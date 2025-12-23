package com.tapas.qb.ingestion.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.Instant;

@Setter
@Getter
@Entity
@Table(name = "order_events", schema = "ingestion")
public class OrderEvent {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long orderId;

    private Long merchantId;

    private String eventType;

    @Column(name = "payload")
    private String payload;

    private Instant createdAt;

    private Boolean processed;

    private Instant processedAt;

}
