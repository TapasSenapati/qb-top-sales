package com.tapas.qb.ingestion.api.dto;

import java.time.Instant;
import java.util.List;

public record OrderCreateRequest(
        String externalOrderId,
        Long merchantId,
        Instant orderDate,
        String currency,
        List<OrderItemRequest> items
) {}
