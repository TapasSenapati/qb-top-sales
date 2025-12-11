package com.tapas.qb.ingestion.service.impl;

import com.tapas.qb.ingestion.api.dto.OrderCreateRequest;
import com.tapas.qb.ingestion.api.dto.OrderCreateResponse;
import com.tapas.qb.ingestion.api.dto.OrderItemRequest;
import com.tapas.qb.ingestion.domain.Order;
import com.tapas.qb.ingestion.domain.OrderEvent;
import com.tapas.qb.ingestion.domain.OrderItem;
import com.tapas.qb.ingestion.repository.OrderEventRepository;
import com.tapas.qb.ingestion.repository.OrderItemRepository;
import com.tapas.qb.ingestion.repository.OrderRepository;
import com.tapas.qb.ingestion.service.OrderService;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.Instant;

@Service
public class OrderServiceImpl implements OrderService {

    private final OrderRepository orderRepository;
    private final OrderItemRepository orderItemRepository;
    private final OrderEventRepository orderEventRepository;

    public OrderServiceImpl(OrderRepository orderRepository,
                            OrderItemRepository orderItemRepository,
                            OrderEventRepository orderEventRepository) {
        this.orderRepository = orderRepository;
        this.orderItemRepository = orderItemRepository;
        this.orderEventRepository = orderEventRepository;
    }

    @Override
    @Transactional
    public OrderCreateResponse createOrder(OrderCreateRequest request) {
        // compute totals
        BigDecimal totalAmount = request.items().stream()
                .map(i -> i.unitPrice().multiply(BigDecimal.valueOf(i.quantity())))
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        // save order
        Order order = new Order();
        order.setMerchantId(request.merchantId());
        order.setOrderDate(request.orderDate());
        order.setCurrency(request.currency());
        order.setTotalAmount(totalAmount);
        order = orderRepository.save(order);

        // save items
        for (OrderItemRequest itemReq : request.items()) {
            OrderItem item = new OrderItem();
            item.setOrderId(order.getId());
            item.setProductId(itemReq.productId());
            item.setQuantity(itemReq.quantity());
            item.setUnitPrice(itemReq.unitPrice());
            item.setLineAmount(itemReq.unitPrice()
                    .multiply(BigDecimal.valueOf(itemReq.quantity())));
            orderItemRepository.save(item);
        }

        // create outbox event payload (you can refine structure later)
        String payloadJson = /* build JSON string, e.g. with Jackson ObjectMapper */ "{}";

        OrderEvent event = new OrderEvent();
        event.setOrderId(order.getId());
        event.setMerchantId(request.merchantId());
        event.setEventType("ORDER_CREATED");
        event.setPayload(payloadJson);
        event.setCreatedAt(Instant.now());
        event.setProcessed(false);
        orderEventRepository.save(event);

        return new OrderCreateResponse(
                order.getId(),
                request.merchantId(),
                totalAmount,
                request.currency(),
                request.items().size(),
                "CREATED"
        );
    }
}
