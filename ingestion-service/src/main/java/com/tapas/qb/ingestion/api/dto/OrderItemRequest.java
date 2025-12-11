package com.tapas.qb.ingestion.api.dto;

import java.math.BigDecimal;

public record OrderItemRequest(
        Long productId,
        Integer quantity,
        BigDecimal unitPrice
) {}
