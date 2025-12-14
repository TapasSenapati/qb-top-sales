package com.tapas.qb.forecasting.domain;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(
        name = "category_sales_agg",
        schema = "forecasting",
        uniqueConstraints = @UniqueConstraint(
                name = "uq_category_sales_bucket",
                columnNames = {
                        "merchant_id",
                        "category_id",
                        "bucket_type",
                        "bucket_start"
                }
        )
)
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

    /* getters & setters only — no logic */

    public Long getId() {
        return id;
    }

    public Long getMerchantId() {
        return merchantId;
    }

    public void setMerchantId(Long merchantId) {
        this.merchantId = merchantId;
    }

    public Long getCategoryId() {
        return categoryId;
    }

    public void setCategoryId(Long categoryId) {
        this.categoryId = categoryId;
    }

    public String getBucketType() {
        return bucketType;
    }

    public void setBucketType(String bucketType) {
        this.bucketType = bucketType;
    }

    public Instant getBucketStart() {
        return bucketStart;
    }

    public void setBucketStart(Instant bucketStart) {
        this.bucketStart = bucketStart;
    }

    public Instant getBucketEnd() {
        return bucketEnd;
    }

    public void setBucketEnd(Instant bucketEnd) {
        this.bucketEnd = bucketEnd;
    }

    public BigDecimal getTotalSalesAmount() {
        return totalSalesAmount;
    }

    public void setTotalSalesAmount(BigDecimal totalSalesAmount) {
        this.totalSalesAmount = totalSalesAmount;
    }

    public Long getTotalUnitsSold() {
        return totalUnitsSold;
    }

    public void setTotalUnitsSold(Long totalUnitsSold) {
        this.totalUnitsSold = totalUnitsSold;
    }

    public Long getOrderCount() {
        return orderCount;
    }

    public void setOrderCount(Long orderCount) {
        this.orderCount = orderCount;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
    }
}
