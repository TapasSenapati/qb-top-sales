package com.tapas.qb.aggregation.dto;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

/**
 * Event payload consumed from order-events Kafka topic.
 * Uses orderId for idempotency (tracks processed orders in DuckDB).
 */
public record OrderEventPayload(
                Long orderId, // Used for idempotency
                Long merchantId,
                Instant orderDate,
                List<Item> items) {
        public record Item(
                        Long categoryId,
                        int quantity,
                        BigDecimal lineAmount) {
        }
}
