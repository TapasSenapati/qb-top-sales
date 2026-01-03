package com.tapas.qb.aggregation.dto;

import com.tapas.qb.aggregation.repository.TopCategoryRow;
import java.math.BigDecimal;

public record TopCategoryDto(
        Long categoryId,
        String categoryName,
        BigDecimal totalSalesAmount,
        Long totalUnitsSold,
        Long orderCount) implements TopCategoryRow {
    @Override
    public Long getCategoryId() {
        return categoryId();
    }

    @Override
    public String getCategoryName() {
        return categoryName();
    }

    @Override
    public BigDecimal getTotalSalesAmount() {
        return totalSalesAmount();
    }

    @Override
    public Long getTotalUnitsSold() {
        return totalUnitsSold();
    }

    @Override
    public Long getOrderCount() {
        return orderCount();
    }
}
