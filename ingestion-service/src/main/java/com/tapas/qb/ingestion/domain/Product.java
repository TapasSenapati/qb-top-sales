package com.tapas.qb.ingestion.domain;

import jakarta.persistence.*;

@Entity
@Table(name = "products", schema = "ingestion")
public class Product {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long merchantId;
    private Long categoryId;
    private String name;
    // getters/setters
}
