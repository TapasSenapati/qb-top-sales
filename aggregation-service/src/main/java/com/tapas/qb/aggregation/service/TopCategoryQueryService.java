package com.tapas.qb.aggregation.service;

import com.tapas.qb.aggregation.repository.CategorySalesQueryRepository;
import com.tapas.qb.aggregation.repository.TopCategoryRow;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;

@Service
public class TopCategoryQueryService {

    private final CategorySalesQueryRepository repository;

    public TopCategoryQueryService(CategorySalesQueryRepository repository) {
        this.repository = repository;
    }

    public List<TopCategoryRow> topCategories(
            Long merchantId,
            String bucketType,
            Instant bucketStart,
            Instant bucketEnd,
            int limit) {
        if ("CUSTOM".equalsIgnoreCase(bucketType) && bucketEnd != null) {
            return repository.findTopCategoriesInRange(
                    merchantId,
                    bucketStart,
                    bucketEnd,
                    limit);
        }

        return repository.findTopCategories(
                merchantId,
                bucketType,
                bucketStart,
                limit);
    }
}
