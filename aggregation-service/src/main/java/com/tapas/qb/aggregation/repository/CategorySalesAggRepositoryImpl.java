package com.tapas.qb.aggregation.repository;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.util.Collection;

/**
 * Repository implementation for writing sales aggregations to ClickHouse.
 * Uses ClickHouse's ReplacingMergeTree engine for deduplication.
 * 
 * Delta values are inserted; read queries should use SUM() with GROUP BY
 * for accurate totals, or switch to SummingMergeTree engine.
 */
@Repository
public class CategorySalesAggRepositoryImpl implements CategorySalesAggRepositoryCustom {

    private static final Logger log = LoggerFactory.getLogger(CategorySalesAggRepositoryImpl.class);

    private final JdbcTemplate clickHouseJdbcTemplate;

    public CategorySalesAggRepositoryImpl(
            @Qualifier("clickHouseJdbcTemplate") JdbcTemplate clickHouseJdbcTemplate) {
        this.clickHouseJdbcTemplate = clickHouseJdbcTemplate;
    }

    @Override
    public void bulkUpsert(String bucketType, Collection<UpsertData> data) {
        if (data == null || data.isEmpty()) {
            return;
        }

        writeToClickHouse(bucketType, data);
    }

    private void writeToClickHouse(String bucketType, Collection<UpsertData> data) {
        // Use epoch milliseconds for DateTime64(3) compatibility
        String insertSql = """
                INSERT INTO category_sales_agg
                (merchant_id, category_id, bucket_type, bucket_start, bucket_end,
                 total_sales_amount, total_units_sold, order_count, updated_at)
                VALUES (?, ?, ?, fromUnixTimestamp64Milli(?), fromUnixTimestamp64Milli(?), ?, ?, ?, now64())
                """;

        int successCount = 0;
        for (UpsertData item : data) {
            try {
                clickHouseJdbcTemplate.update(insertSql,
                        item.merchantId(),
                        item.categoryId(),
                        bucketType,
                        item.bucketStart().toEpochMilli(),
                        item.bucketEnd().toEpochMilli(),
                        item.totalSalesAmount(),
                        item.totalUnitsSold(),
                        item.orderCount());
                successCount++;
            } catch (Exception e) {
                log.error("Failed to write to ClickHouse for category {}: {}",
                        item.categoryId(), e.getMessage(), e);
            }
        }

        if (successCount > 0) {
            log.info("Wrote {} aggregation records to ClickHouse for bucket {}", successCount, bucketType);
        }
    }
}
