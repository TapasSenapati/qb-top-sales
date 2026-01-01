package com.tapas.qb.ingestion.api.dto;

import java.math.BigDecimal;

public record OrderCreateResponse(
                Long orderId,
                String externalOrderId,
                Long merchantId,
                BigDecimal totalAmount,
                Integer itemCount,
                String status) {
}
