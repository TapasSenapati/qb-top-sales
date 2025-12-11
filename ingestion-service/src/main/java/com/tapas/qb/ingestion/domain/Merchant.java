package com.tapas.qb.ingestion.domain;

import jakarta.persistence.*;

@Entity
@Table(name = "merchants", schema = "ingestion")
public class Merchant {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;
    // getters/setters
}
