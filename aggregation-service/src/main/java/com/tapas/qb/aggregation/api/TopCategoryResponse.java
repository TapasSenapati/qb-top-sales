package com.tapas.qb.aggregation.api;

import com.tapas.qb.aggregation.repository.TopCategoryRow;

import java.math.BigDecimal;

public record TopCategoryResponse(
        Long categoryId,
        BigDecimal totalSalesAmount,
        Long totalUnitsSold,
        Long orderCount
) {
    public static TopCategoryResponse from(TopCategoryRow row) {
        return new TopCategoryResponse(
                row.getCategoryId(),
                row.getTotalSalesAmount(),
                row.getTotalUnitsSold(),
                row.getOrderCount()
        );
    }
}
