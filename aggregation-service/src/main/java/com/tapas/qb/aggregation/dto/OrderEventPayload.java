package com.tapas.qb.aggregation.dto;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record OrderEventPayload(
        Long eventId,
        Long orderId,
        String externalOrderId,
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
