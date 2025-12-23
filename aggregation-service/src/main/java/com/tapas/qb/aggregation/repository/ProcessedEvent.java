package com.tapas.qb.aggregation.repository;

import java.time.Instant;

/**
 * Record for tracking processed orders in DuckDB.
 * Uses orderId for idempotency (not JPA entity, just a data holder).
 */
public class ProcessedEvent {

    private Long orderId;
    private Instant processedAt;

    protected ProcessedEvent() {
    }

    public ProcessedEvent(Long orderId, Instant processedAt) {
        this.orderId = orderId;
        this.processedAt = processedAt;
    }

    public Long getOrderId() {
        return orderId;
    }

    public Instant getProcessedAt() {
        return processedAt;
    }
}
