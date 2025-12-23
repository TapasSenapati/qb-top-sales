package com.tapas.qb.aggregation.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.math.BigDecimal;
import java.time.Instant;

@Getter
@Setter
@Entity
@Table(name = "category_sales_agg", schema = "forecasting", uniqueConstraints = @UniqueConstraint(name = "uq_category_sales_bucket", columnNames = {
        "merchant_id",
        "category_id",
        "bucket_type",
        "bucket_start"
}))
public class CategorySalesAgg {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "merchant_id", nullable = false)
    private Long merchantId;

    @Column(name = "category_id", nullable = false)
    private Long categoryId;

    @Column(name = "bucket_type", nullable = false)
    private String bucketType; // DAY | WEEK | MONTH

    @Column(name = "bucket_start", nullable = false)
    private Instant bucketStart;

    @Column(name = "bucket_end", nullable = false)
    private Instant bucketEnd;

    @Column(name = "total_sales_amount", nullable = false)
    private BigDecimal totalSalesAmount;

    @Column(name = "total_units_sold", nullable = false)
    private Long totalUnitsSold;

    @Column(name = "order_count", nullable = false)
    private Long orderCount;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;
}
