package com.tapas.qb.aggregation.repository;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * Record for tracking processed orders in DuckDB.
 * Uses orderId for idempotency (not JPA entity, just a data holder).
 */
@Getter
@NoArgsConstructor
@AllArgsConstructor
public class ProcessedEvent {

    private Long orderId;
    private Instant processedAt;
}
