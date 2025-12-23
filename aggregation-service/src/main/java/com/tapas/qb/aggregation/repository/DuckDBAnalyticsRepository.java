package com.tapas.qb.aggregation.repository;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.util.Collection;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Repository for DuckDB analytics operations.
 * Handles writes to category_sales_agg and processed_events tables in DuckDB.
 */
@Repository
public class DuckDBAnalyticsRepository {

    private static final Logger logger = LoggerFactory.getLogger(DuckDBAnalyticsRepository.class);

    private final JdbcTemplate duckdbJdbcTemplate;

    public DuckDBAnalyticsRepository(@Qualifier("duckdbJdbcTemplate") JdbcTemplate duckdbJdbcTemplate) {
        this.duckdbJdbcTemplate = duckdbJdbcTemplate;
    }

    /**
     * Bulk upsert aggregated sales data into DuckDB.
     * Uses DELETE + INSERT pattern since DuckDB doesn't support ON CONFLICT with
     * UPDATE additions.
     */
    public void bulkUpsert(String bucketType, Collection<UpsertData> data) {
        if (data == null || data.isEmpty()) {
            return;
        }

        logger.debug("Upserting {} records for bucket type {} to DuckDB", data.size(), bucketType);

        for (UpsertData item : data) {
            // First, try to get existing values
            String selectSql = """
                    SELECT total_sales_amount, total_units_sold, order_count, id
                    FROM category_sales_agg
                    WHERE merchant_id = ? AND category_id = ? AND bucket_type = ? AND bucket_start = ?
                    """;

            var existing = duckdbJdbcTemplate.query(selectSql,
                    (rs, rowNum) -> new Object[] {
                            rs.getBigDecimal(1),
                            rs.getLong(2),
                            rs.getLong(3),
                            rs.getLong(4)
                    },
                    item.merchantId(),
                    item.categoryId(),
                    bucketType,
                    Timestamp.from(item.bucketStart()));

            if (existing.isEmpty()) {
                // Insert new record
                String insertSql = """
                        INSERT INTO category_sales_agg
                        (id, merchant_id, category_id, bucket_type, bucket_start, bucket_end,
                         total_sales_amount, total_units_sold, order_count, updated_at)
                        VALUES (nextval('category_sales_agg_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?, now())
                        """;

                duckdbJdbcTemplate.update(insertSql,
                        item.merchantId(),
                        item.categoryId(),
                        bucketType,
                        Timestamp.from(item.bucketStart()),
                        Timestamp.from(item.bucketEnd()),
                        item.totalSalesAmount(),
                        item.totalUnitsSold(),
                        item.orderCount());
            } else {
                // Update existing record by adding to current values
                Object[] row = existing.get(0);
                var currentAmount = (java.math.BigDecimal) row[0];
                var currentUnits = (Long) row[1];
                var currentCount = (Long) row[2];
                var id = (Long) row[3];

                var newAmount = currentAmount.add(item.totalSalesAmount());
                var newUnits = currentUnits + item.totalUnitsSold();
                var newCount = currentCount + item.orderCount();

                String updateSql = """
                        UPDATE category_sales_agg
                        SET total_sales_amount = ?, total_units_sold = ?, order_count = ?, updated_at = now()
                        WHERE id = ?
                        """;

                duckdbJdbcTemplate.update(updateSql, newAmount, newUnits, newCount, id);
            }
        }

        logger.debug("Successfully upserted {} records to DuckDB", data.size());
    }

    /**
     * Save processed events to DuckDB for idempotency tracking.
     */
    public void saveProcessedEvents(Collection<ProcessedEvent> events) {
        if (events == null || events.isEmpty()) {
            return;
        }

        String sql = """
                INSERT INTO processed_events (event_id, processed_at)
                VALUES (?, ?)
                ON CONFLICT DO NOTHING
                """;

        for (ProcessedEvent event : events) {
            try {
                duckdbJdbcTemplate.update(sql, event.getEventId(), Timestamp.from(event.getProcessedAt()));
            } catch (Exception e) {
                // Event might already exist (idempotency), ignore
                logger.debug("Event {} already processed or error: {}", event.getEventId(), e.getMessage());
            }
        }
    }

    /**
     * Find which event IDs have already been processed.
     */
    public Set<Long> findExistingEventIds(Collection<Long> eventIds) {
        if (eventIds == null || eventIds.isEmpty()) {
            return Set.of();
        }

        String placeholders = eventIds.stream()
                .map(id -> "?")
                .collect(Collectors.joining(","));

        String sql = "SELECT event_id FROM processed_events WHERE event_id IN (" + placeholders + ")";

        return duckdbJdbcTemplate.query(sql,
                eventIds.toArray(),
                (rs, rowNum) -> rs.getLong(1))
                .stream()
                .collect(Collectors.toSet());
    }

    /**
     * Health check - verify DuckDB connection and tables exist.
     */
    public boolean healthCheck() {
        try {
            var count = duckdbJdbcTemplate.queryForObject(
                    "SELECT COUNT(*) FROM category_sales_agg", Integer.class);
            return count != null;
        } catch (Exception e) {
            logger.error("DuckDB health check failed: {}", e.getMessage());
            return false;
        }
    }
}
