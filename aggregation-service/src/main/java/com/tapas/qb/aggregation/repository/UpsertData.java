package com.tapas.qb.aggregation.repository;

import java.math.BigDecimal;
import java.time.Instant;

public record UpsertData(
        Long merchantId,
        Long categoryId,
        Instant bucketStart,
        Instant bucketEnd,
        BigDecimal totalSalesAmount,
        Long totalUnitsSold,
        long orderCount
) {
}
