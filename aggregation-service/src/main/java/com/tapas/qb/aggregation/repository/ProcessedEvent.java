package com.tapas.qb.aggregation.repository;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;

@Entity
@Table(name = "processed_events", schema = "forecasting")
public class ProcessedEvent {

    @Id
    private Long eventId;

    private Instant processedAt;

    protected ProcessedEvent() {}

    public ProcessedEvent(Long eventId, Instant processedAt) {
        this.eventId = eventId;
        this.processedAt = processedAt;
    }
}
