package com.tapas.qb.ingestion.events;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

/**
 * Simplified event payload for order-events Kafka topic.
 * Uses orderId for idempotency in downstream services.
 * 
 * TODO (Production): Use TSID/Snowflake for globally unique,
 * time-sorted IDs when scaling to multiple ingestion instances.
 */
public record OrderCreatedEventPayload(
                Long orderId, // Used for idempotency downstream
                Long merchantId,
                Instant orderDate,
                List<Item> items) {
        public record Item(
                        Long categoryId,
                        Integer quantity,
                        BigDecimal lineAmount) {
        }
}
