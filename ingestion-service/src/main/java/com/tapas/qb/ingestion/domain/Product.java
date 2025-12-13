package com.tapas.qb.ingestion.domain;

import jakarta.persistence.*;

@Entity
@Table(name = "products", schema = "ingestion")
public class Product {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long merchantId;
    @Column(name = "category_id", nullable = false)
    private Long categoryId;
    private String name;
    public Long getId() {
        return id;
    }

    public Long getCategoryId() {
        return categoryId;
    }
}
