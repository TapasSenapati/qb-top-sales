package com.tapas.qb.forecasting.service;

import com.tapas.qb.forecasting.repository.CategorySalesQueryRepository;
import com.tapas.qb.forecasting.repository.TopCategoryRow;
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
            int limit
    ) {
        return repository.findTopCategories(
                merchantId,
                bucketType,
                bucketStart,
                limit
        );
    }
}
