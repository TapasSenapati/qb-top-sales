package com.tapas.qb.aggregation.service;

import com.tapas.qb.aggregation.dto.OrderEventPayload;
import com.tapas.qb.aggregation.repository.CategorySalesAggRepository;
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
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Aggregates order events into time-bucketed sales summaries (DAY, WEEK,
 * MONTH).
 * 
 * SINGLE-WRITE ARCHITECTURE:
 * - PostgreSQL: All data written to forecasting schema for both real-time
 * API queries and forecasting-worker batch processing
 * 
 * CURRENCY: Single currency per merchant is enforced at schema level
 * (ingestion.merchants.currency). Amounts are summed directly without
 * conversion.
 */
@Service
public class CategorySalesAggregator {
        private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(CategorySalesAggregator.class);

        private final ProcessedEventRepository processedEventRepo;
        private final CategorySalesAggRepository postgresRepo;

        public CategorySalesAggregator(ProcessedEventRepository processedEventRepo,
                        CategorySalesAggRepository postgresRepo) {
                this.processedEventRepo = processedEventRepo;
                this.postgresRepo = postgresRepo;
        }

        @Transactional
        public void aggregate(List<OrderEventPayload> events) {

                var orderIds = events.stream()
                                .map(OrderEventPayload::orderId)
                                .toList();

                // Check idempotency against Postgres (forecasting.processed_events)
                var existingEvents = processedEventRepo.findAllById(orderIds);
                var existingOrderIds = existingEvents.stream()
                                .map(ProcessedEvent::getOrderId)
                                .toList();

                var unprocessedEvents = events.stream()
                                .filter(e -> !existingOrderIds.contains(e.orderId()))
                                .toList();

                if (unprocessedEvents.isEmpty()) {
                        return; // all events were already processed
                }

                // Save processed orders to Postgres for idempotency
                var processedEvents = unprocessedEvents.stream()
                                .map(e -> new ProcessedEvent(e.orderId(), Instant.now()))
                                .toList();
                processedEventRepo.saveAll(processedEvents);

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

                // Convert to UpsertData
                var dayData = toUpsertData(dayAggregates, ChronoUnit.DAYS);
                var weekData = toUpsertData(weekAggregates, 7, ChronoUnit.DAYS);
                var monthData = toUpsertData(monthAggregates, 1, ChronoUnit.MONTHS);

                // === SINGLE-WRITE: Write ONLY to Postgres ===

                logger.info("Writing aggregates to Postgres: {} day, {} week, {} month records",
                                dayAggregates.size(), weekAggregates.size(), monthAggregates.size());

                writeToPostgres(dayData, weekData, monthData);
        }

        /**
         * Write aggregates to Postgres for real-time API queries.
         */
        private void writeToPostgres(List<UpsertData> dayData,
                        List<UpsertData> weekData,
                        List<UpsertData> monthData) {
                try {
                        for (UpsertData data : dayData) {
                                postgresRepo.upsertDayAggregate(
                                                data.merchantId(),
                                                data.categoryId(),
                                                data.bucketStart(),
                                                data.bucketEnd(),
                                                data.totalSalesAmount(),
                                                data.totalUnitsSold());
                        }

                        for (UpsertData data : weekData) {
                                postgresRepo.upsertWeekAggregate(
                                                data.merchantId(),
                                                data.categoryId(),
                                                data.bucketStart(),
                                                data.bucketEnd(),
                                                data.totalSalesAmount(),
                                                data.totalUnitsSold());
                        }

                        for (UpsertData data : monthData) {
                                postgresRepo.upsertMonthAggregate(
                                                data.merchantId(),
                                                data.categoryId(),
                                                data.bucketStart(),
                                                data.bucketEnd(),
                                                data.totalSalesAmount(),
                                                data.totalUnitsSold());
                        }

                        logger.debug("Successfully wrote aggregates to Postgres");
                } catch (Exception e) {
                        logger.error("Failed to write aggregates to Postgres", e);
                        // Re-throw to ensure transaction rollback
                        throw e;
                }
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