package com.tapas.qb.ingestion.api.dto;

import java.math.BigDecimal;

public record OrderCreateResponse(
        Long orderId,
        Long merchantId,
        BigDecimal totalAmount,
        String currency,
        Integer itemCount,
        String status
) {}

