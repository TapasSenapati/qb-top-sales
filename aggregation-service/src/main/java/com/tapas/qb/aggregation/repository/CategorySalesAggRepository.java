package com.tapas.qb.aggregation.repository;

import com.tapas.qb.aggregation.domain.CategorySalesAgg;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;

import java.math.BigDecimal;
import java.time.Instant;

public interface CategorySalesAggRepository
        extends JpaRepository<CategorySalesAgg, Long>, CategorySalesAggRepositoryCustom {

    @Modifying
    @Query(value = """
        INSERT INTO forecasting.category_sales_agg
        (merchant_id, category_id, bucket_type, bucket_start, bucket_end,
         total_sales_amount, total_units_sold, order_count, updated_at)
        VALUES
        (:merchantId, :categoryId, 'DAY', :bucketStart, :bucketEnd,
         :amount, :quantity, 1, now())
        ON CONFLICT (merchant_id, category_id, bucket_type, bucket_start)
        DO UPDATE SET
            total_sales_amount = category_sales_agg.total_sales_amount + EXCLUDED.total_sales_amount,
            total_units_sold   = category_sales_agg.total_units_sold + EXCLUDED.total_units_sold,
            order_count        = category_sales_agg.order_count + 1,
            updated_at         = now()
        """,
            nativeQuery = true)
    void upsertDayAggregate(
            Long merchantId,
            Long categoryId,
            Instant bucketStart,
            Instant bucketEnd,
            BigDecimal amount,
            Long quantity
    );

    @Modifying
    @Query(value = """
    INSERT INTO forecasting.category_sales_agg
    (merchant_id, category_id, bucket_type, bucket_start, bucket_end,
     total_sales_amount, total_units_sold, order_count, updated_at)
    VALUES
    (:merchantId, :categoryId, 'WEEK', :bucketStart, :bucketEnd,
     :amount, :quantity, 1, now())
    ON CONFLICT (merchant_id, category_id, bucket_type, bucket_start)
    DO UPDATE SET
        total_sales_amount = category_sales_agg.total_sales_amount + EXCLUDED.total_sales_amount,
        total_units_sold   = category_sales_agg.total_units_sold + EXCLUDED.total_units_sold,
        order_count        = category_sales_agg.order_count + 1,
        updated_at         = now()
    """,
            nativeQuery = true)
    void upsertWeekAggregate(
            Long merchantId,
            Long categoryId,
            Instant bucketStart,
            Instant bucketEnd,
            BigDecimal amount,
            Long quantity
    );

    @Modifying
    @Query(value = """
    INSERT INTO forecasting.category_sales_agg
    (merchant_id, category_id, bucket_type, bucket_start, bucket_end,
     total_sales_amount, total_units_sold, order_count, updated_at)
    VALUES
    (:merchantId, :categoryId, 'MONTH', :bucketStart, :bucketEnd,
     :amount, :quantity, 1, now())
    ON CONFLICT (merchant_id, category_id, bucket_type, bucket_start)
    DO UPDATE SET
        total_sales_amount = category_sales_agg.total_sales_amount + EXCLUDED.total_sales_amount,
        total_units_sold   = category_sales_agg.total_units_sold + EXCLUDED.total_units_sold,
        order_count        = category_sales_agg.order_count + 1,
        updated_at         = now()
    """,
            nativeQuery = true)
    void upsertMonthAggregate(
            Long merchantId,
            Long categoryId,
            Instant bucketStart,
            Instant bucketEnd,
            BigDecimal amount,
            Long quantity
    );


}
