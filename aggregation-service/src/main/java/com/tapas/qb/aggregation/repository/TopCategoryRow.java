package com.tapas.qb.aggregation.repository;

import java.math.BigDecimal;

public interface TopCategoryRow {
    Long getCategoryId();
    BigDecimal getTotalSalesAmount();
    Long getTotalUnitsSold();
    Long getOrderCount();
}
