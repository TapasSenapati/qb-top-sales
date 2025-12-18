package com.tapas.qb.ingestion.events;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record OrderCreatedEventPayload(
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
            Integer quantity,
            BigDecimal unitPrice,
            BigDecimal lineAmount
    ) {}
}
