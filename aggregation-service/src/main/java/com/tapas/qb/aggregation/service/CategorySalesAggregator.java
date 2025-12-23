package com.tapas.qb.aggregation.service;

import com.tapas.qb.aggregation.dto.OrderEventPayload;
import com.tapas.qb.aggregation.repository.CategorySalesAggRepository;
import com.tapas.qb.aggregation.repository.DuckDBAnalyticsRepository;
import com.tapas.qb.aggregation.repository.ProcessedEvent;
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
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class CategorySalesAggregator {
        private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(CategorySalesAggregator.class);

        private final CategorySalesAggRepository aggRepo;
        private final DuckDBAnalyticsRepository duckDBRepo;

        public CategorySalesAggregator(
                        CategorySalesAggRepository aggRepo,
                        DuckDBAnalyticsRepository duckDBRepo) {
                this.aggRepo = aggRepo;
                this.duckDBRepo = duckDBRepo;
        }

        @Transactional
        public void aggregate(List<OrderEventPayload> events) {

                var orderIds = events.stream()
                                .map(OrderEventPayload::orderId)
                                .toList();

                // Check idempotency against DuckDB
                var existingOrderIds = duckDBRepo.findExistingOrderIds(orderIds);

                var unprocessedEvents = events.stream()
                                .filter(e -> !existingOrderIds.contains(e.orderId()))
                                .toList();

                if (unprocessedEvents.isEmpty()) {
                        return; // all events were already processed
                }

                // Save processed orders to DuckDB for idempotency
                var processedEvents = unprocessedEvents.stream()
                                .map(e -> new ProcessedEvent(e.orderId(), Instant.now()))
                                .toList();
                duckDBRepo.saveProcessedOrders(processedEvents);

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