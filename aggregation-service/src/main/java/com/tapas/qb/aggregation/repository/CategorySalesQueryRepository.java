package com.tapas.qb.aggregation.repository;

import com.tapas.qb.aggregation.domain.CategorySalesAgg;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.Repository;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.List;

public interface CategorySalesQueryRepository
    extends Repository<CategorySalesAgg, Long> {

  @Query(value = """
      SELECT
        csa.category_id        AS categoryId,
        c.name                 AS categoryName,
        csa.total_sales_amount AS totalSalesAmount,
        csa.total_units_sold   AS totalUnitsSold,
        csa.order_count        AS orderCount
      FROM forecasting.category_sales_agg csa
      JOIN ingestion.categories c ON c.id = csa.category_id
      WHERE csa.merchant_id = :merchantId
        AND csa.bucket_type = :bucketType
        AND csa.bucket_start = :bucketStart
      ORDER BY csa.total_sales_amount DESC
      LIMIT :limit
      """, nativeQuery = true)
  List<TopCategoryRow> findTopCategories(
      @Param("merchantId") Long merchantId,
      @Param("bucketType") String bucketType,
      @Param("bucketStart") Instant bucketStart,
      @Param("limit") int limit);

  @Query(value = """
      SELECT
        csa.category_id        AS categoryId,
        c.name                 AS categoryName,
        SUM(csa.total_sales_amount) AS totalSalesAmount,
        SUM(csa.total_units_sold)   AS totalUnitsSold,
        SUM(csa.order_count)        AS orderCount
      FROM forecasting.category_sales_agg csa
      JOIN ingestion.categories c ON c.id = csa.category_id
      WHERE csa.merchant_id = :merchantId
        AND csa.bucket_type = 'DAY'
        AND csa.bucket_start >= :startDate
        AND csa.bucket_start <= :endDate
      GROUP BY csa.category_id, c.name
      ORDER BY totalSalesAmount DESC
      LIMIT :limit
      """, nativeQuery = true)
  List<TopCategoryRow> findTopCategoriesInRange(
      @Param("merchantId") Long merchantId,
      @Param("startDate") Instant startDate,
      @Param("endDate") Instant endDate,
      @Param("limit") int limit);
}
