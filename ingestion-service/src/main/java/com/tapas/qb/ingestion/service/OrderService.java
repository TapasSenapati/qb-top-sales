package com.tapas.qb.ingestion.service;

import com.tapas.qb.ingestion.api.dto.OrderCreateRequest;
import com.tapas.qb.ingestion.api.dto.OrderCreateResponse;

public interface OrderService {
    OrderCreateResponse createOrder(OrderCreateRequest request);
}
