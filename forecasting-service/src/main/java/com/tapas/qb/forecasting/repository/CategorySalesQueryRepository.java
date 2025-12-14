package com.tapas.qb.forecasting.repository;

import com.tapas.qb.forecasting.domain.CategorySalesAgg;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.Repository;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.List;

public interface CategorySalesQueryRepository
        extends Repository<CategorySalesAgg, Long> {

    @Query(value = """
        SELECT
          category_id        AS categoryId,
          total_sales_amount AS totalSalesAmount,
          total_units_sold   AS totalUnitsSold,
          order_count        AS orderCount
        FROM forecasting.category_sales_agg
        WHERE merchant_id = :merchantId
          AND bucket_type = :bucketType
          AND bucket_start = :bucketStart
        ORDER BY total_sales_amount DESC
        LIMIT :limit
        """,
            nativeQuery = true)
    List<TopCategoryRow> findTopCategories(
            @Param("merchantId") Long merchantId,
            @Param("bucketType") String bucketType,
            @Param("bucketStart") Instant bucketStart,
            @Param("limit") int limit
    );
}
