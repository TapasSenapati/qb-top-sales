package com.tapas.qb.ingestion.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
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
}
