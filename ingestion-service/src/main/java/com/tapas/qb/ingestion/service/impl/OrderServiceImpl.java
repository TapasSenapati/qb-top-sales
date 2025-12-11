package com.tapas.qb.ingestion.service.impl;

import com.tapas.qb.ingestion.api.dto.OrderCreateRequest;
import com.tapas.qb.ingestion.api.dto.OrderCreateResponse;
import com.tapas.qb.ingestion.service.OrderService;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;

@Service
public class OrderServiceImpl implements OrderService {

    @Override
    public OrderCreateResponse createOrder(OrderCreateRequest request) {
        // Temporary stub implementation; will be replaced with real DB logic
        BigDecimal totalAmount = request.items().stream()
                .map(i -> i.unitPrice().multiply(BigDecimal.valueOf(i.quantity())))
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        return new OrderCreateResponse(
                1L,                       // dummy orderId
                request.merchantId(),
                totalAmount,
                request.currency(),
                request.items().size(),
                "CREATED"
        );
    }
}
