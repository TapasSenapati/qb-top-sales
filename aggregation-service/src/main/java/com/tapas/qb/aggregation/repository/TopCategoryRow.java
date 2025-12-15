package com.tapas.qb.aggregation.repository;

import java.math.BigDecimal;

public interface TopCategoryRow {
    Long getCategoryId();
    String getCategoryName();
    BigDecimal getTotalSalesAmount();
    Long getTotalUnitsSold();
    Long getOrderCount();
}
