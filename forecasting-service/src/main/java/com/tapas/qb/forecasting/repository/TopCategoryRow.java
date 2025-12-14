package com.tapas.qb.forecasting.repository;

import java.math.BigDecimal;

public interface TopCategoryRow {
    Long getCategoryId();
    BigDecimal getTotalSalesAmount();
    Long getTotalUnitsSold();
    Long getOrderCount();
}
