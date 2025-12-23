package com.tapas.qb.ingestion.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.math.BigDecimal;
import java.time.Instant;

@Getter
@Setter
@Entity
@Table(name = "orders", schema = "ingestion")
public class Order {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String externalOrderId;

    private Long merchantId;

    private Instant orderDate;

    private String currency;

    private BigDecimal totalAmount;
}
