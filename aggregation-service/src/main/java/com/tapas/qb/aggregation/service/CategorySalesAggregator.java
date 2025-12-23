package com.tapas.qb.aggregation.service;

import com.tapas.qb.aggregation.dto.OrderEventPayload;
import com.tapas.qb.aggregation.repository.CategorySalesAggRepository;
import com.tapas.qb.aggregation.repository.DuckDBAnalyticsRepository;
import com.tapas.qb.aggregation.repository.ProcessedEvent;
import com.tapas.qb.aggregation.repository.ProcessedEventRepository;
import com.tapas.qb.aggregation.repository.UpsertData;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.DayOfWeek;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.temporal.ChronoUnit;
import java.time.temporal.TemporalAdjusters;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class CategorySalesAggregator {
    private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(CategorySalesAggregator.class);

    private final CategorySalesAggRepository aggRepo;
    private final ProcessedEventRepository processedRepo;
    private final DuckDBAnalyticsRepository duckDBRepo;

    public CategorySalesAggregator(
            CategorySalesAggRepository aggRepo,
            ProcessedEventRepository processedRepo,
            DuckDBAnalyticsRepository duckDBRepo) {
        this.aggRepo = aggRepo;
        this.processedRepo = processedRepo;
        this.duckDBRepo = duckDBRepo;
    }

    @Transactional
    public void aggregate(List<OrderEventPayload> events) {

        var eventIds = events.stream()
                .map(OrderEventPayload::eventId)
                .toList();

        // Check idempotency against DuckDB
        var existingEventIds = duckDBRepo.findExistingEventIds(eventIds);

        var unprocessedEvents = events.stream()
                .filter(e -> !existingEventIds.contains(e.eventId()))
                .toList();

        if (unprocessedEvents.isEmpty()) {
            return; // all events were already processed
        }

        // Save processed events to DuckDB for idempotency
        var processedEvents = unprocessedEvents.stream()
                .map(e -> new ProcessedEvent(e.eventId(), Instant.now()))
                .toList();
        duckDBRepo.saveProcessedEvents(processedEvents);

        var dayAggregates = new HashMap<AggregationKey, Aggregation>();
        var weekAggregates = new HashMap<AggregationKey, Aggregation>();
        var monthAggregates = new HashMap<AggregationKey, Aggregation>();

        for (OrderEventPayload event : unprocessedEvents) {
            for (OrderEventPayload.Item item : event.items()) {
                // Day
                Instant dayBucket = event.orderDate().truncatedTo(ChronoUnit.DAYS);
                var dayKey = new AggregationKey(event.merchantId(), item.categoryId(), dayBucket);
                dayAggregates.computeIfAbsent(dayKey, k -> new Aggregation()).add(item);

                // Week
                Instant weekBucket = weekBucketStart(event.orderDate());
                var weekKey = new AggregationKey(event.merchantId(), item.categoryId(), weekBucket);
                weekAggregates.computeIfAbsent(weekKey, k -> new Aggregation()).add(item);

                // Month
                Instant monthBucket = monthBucketStart(event.orderDate());
                var monthKey = new AggregationKey(event.merchantId(), item.categoryId(), monthBucket);
                monthAggregates.computeIfAbsent(monthKey, k -> new Aggregation()).add(item);
            }
        }

        // Bulk upsert to DuckDB (analytics database)
        logger.info("Writing aggregates to DuckDB: {} day, {} week, {} month records",
                dayAggregates.size(), weekAggregates.size(), monthAggregates.size());

        duckDBRepo.bulkUpsert("DAY", toUpsertData(dayAggregates, ChronoUnit.DAYS));
        duckDBRepo.bulkUpsert("WEEK", toUpsertData(weekAggregates, 7, ChronoUnit.DAYS));
        duckDBRepo.bulkUpsert("MONTH", toUpsertData(monthAggregates, 1, ChronoUnit.MONTHS));
    }

    private List<UpsertData> toUpsertData(Map<AggregationKey, Aggregation> aggregates,
            ChronoUnit bucketSizeUnit) {
        return toUpsertData(aggregates, 1, bucketSizeUnit);
    }

    private List<UpsertData> toUpsertData(Map<AggregationKey, Aggregation> aggregates,
            long bucketSize,
            ChronoUnit bucketSizeUnit) {

        return aggregates.entrySet().stream()
                .map(entry -> {
                    var key = entry.getKey();
                    var agg = entry.getValue();
                    var bucketEnd = key.bucketStart().atZone(ZoneOffset.UTC)
                            .plus(bucketSize, bucketSizeUnit)
                            .toInstant();

                    return new UpsertData(
                            key.merchantId(),
                            key.categoryId(),
                            key.bucketStart(),
                            bucketEnd,
                            agg.totalAmount,
                            agg.totalQuantity,
                            agg.orderCount);
                })
                .toList();
    }

    private record AggregationKey(Long merchantId, Long categoryId, Instant bucketStart) {
    }

    private static class Aggregation {
        BigDecimal totalAmount = BigDecimal.ZERO;
        long totalQuantity = 0;
        long orderCount = 0;

        void add(OrderEventPayload.Item item) {
            totalAmount = totalAmount.add(item.lineAmount());
            totalQuantity += item.quantity();
            orderCount++;
        }
    }

    @Transactional
    @Deprecated
    public void aggregate(OrderEventPayload event) {

        // Try to claim the event
        if (processedRepo.existsById(event.eventId())) {
            return; // already processed → no-op
        }
        processedRepo.save(
                new ProcessedEvent(event.eventId(), Instant.now()));

        Instant dayStart = event.orderDate()
                .truncatedTo(ChronoUnit.DAYS);
        Instant dayEnd = dayStart.plus(1, ChronoUnit.DAYS);

        Instant weekStart = weekBucketStart(event.orderDate());
        Instant weekEnd = weekStart.plus(7, ChronoUnit.DAYS);

        Instant monthStart = monthBucketStart(event.orderDate());
        Instant monthEnd = monthStart
                .atZone(ZoneOffset.UTC)
                .plusMonths(1)
                .toInstant();

        for (OrderEventPayload.Item item : event.items()) {
            aggRepo.upsertDayAggregate(
                    event.merchantId(),
                    item.categoryId(),
                    dayStart,
                    dayEnd,
                    item.lineAmount(),
                    (long) item.quantity());
            aggRepo.upsertWeekAggregate(
                    event.merchantId(),
                    item.categoryId(),
                    weekStart,
                    weekEnd,
                    item.lineAmount(),
                    (long) item.quantity());
            aggRepo.upsertMonthAggregate(
                    event.merchantId(),
                    item.categoryId(),
                    monthStart,
                    monthEnd,
                    item.lineAmount(),
                    (long) item.quantity());
        }
    }

    private static Instant weekBucketStart(Instant orderDate) {
        ZonedDateTime zdt = orderDate.atZone(ZoneOffset.UTC);

        ZonedDateTime weekStart = zdt
                .with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY))
                .truncatedTo(ChronoUnit.DAYS);

        return weekStart.toInstant();
    }

    private static Instant monthBucketStart(Instant orderDate) {
        ZonedDateTime zdt = orderDate.atZone(ZoneOffset.UTC);

        ZonedDateTime monthStart = zdt
                .withDayOfMonth(1)
                .truncatedTo(ChronoUnit.DAYS);

        return monthStart.toInstant();
    }

}