package com.tapas.qb.aggregation.repository;

import com.tapas.qb.aggregation.domain.CategorySalesAgg;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * Repository for CategorySalesAgg entity.
 * 
 * Analytics writes now go to ClickHouse via
 * CategorySalesAggRepositoryCustom.bulkUpsert().
 * This JPA repository is kept for entity management but PostgreSQL analytics
 * tables
 * are no longer the primary data store for aggregations.
 */
public interface CategorySalesAggRepository
                extends JpaRepository<CategorySalesAgg, Long>, CategorySalesAggRepositoryCustom {

        // All analytics writes go to ClickHouse via bulkUpsert() in
        // CategorySalesAggRepositoryImpl
}
