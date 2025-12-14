package com.tapas.qb.forecasting.dto;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record OrderEventPayload(
        Long orderId,
        Long merchantId,
        Instant orderDate,
        String currency,
        List<Item> items
) {
    public record Item(
            Long productId,
            Long categoryId,
            int quantity,
            BigDecimal unitPrice,
            BigDecimal lineAmount
    ) {}
}
