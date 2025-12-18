package com.tapas.qb.aggregation.repository;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.util.Collection;

@Repository
public class CategorySalesAggRepositoryImpl implements CategorySalesAggRepositoryCustom {

    private final JdbcTemplate jdbcTemplate;

    public CategorySalesAggRepositoryImpl(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @Override
    public void bulkUpsert(String bucketType, Collection<UpsertData> data) {
        if (data == null || data.isEmpty()) {
            return;
        }

        String sql = """
            INSERT INTO forecasting.category_sales_agg
            (merchant_id, category_id, bucket_type, bucket_start, bucket_end,
             total_sales_amount, total_units_sold, order_count, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, now())
            ON CONFLICT (merchant_id, category_id, bucket_type, bucket_start)
            DO UPDATE SET
                total_sales_amount = category_sales_agg.total_sales_amount + EXCLUDED.total_sales_amount,
                total_units_sold   = category_sales_agg.total_units_sold + EXCLUDED.total_units_sold,
                order_count        = category_sales_agg.order_count + EXCLUDED.order_count,
                updated_at         = now()
            """;

        jdbcTemplate.batchUpdate(sql, data, data.size(), (ps, item) -> {
            ps.setLong(1, item.merchantId());
            ps.setLong(2, item.categoryId());
            ps.setString(3, bucketType);
            ps.setTimestamp(4, Timestamp.from(item.bucketStart()));
            ps.setTimestamp(5, Timestamp.from(item.bucketEnd()));
            ps.setBigDecimal(6, item.totalSalesAmount());
            ps.setLong(7, item.totalUnitsSold());
            ps.setLong(8, item.orderCount());
        });
    }
}
