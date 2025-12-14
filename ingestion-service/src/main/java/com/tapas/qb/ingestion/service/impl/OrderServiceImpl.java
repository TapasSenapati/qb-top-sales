package com.tapas.qb.ingestion.service.impl;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tapas.qb.ingestion.api.dto.OrderCreateRequest;
import com.tapas.qb.ingestion.api.dto.OrderCreateResponse;
import com.tapas.qb.ingestion.api.dto.OrderItemRequest;
import com.tapas.qb.ingestion.domain.Order;
import com.tapas.qb.ingestion.domain.OrderEvent;
import com.tapas.qb.ingestion.domain.OrderItem;
import com.tapas.qb.ingestion.events.OrderCreatedEventPayload;
import com.tapas.qb.ingestion.repository.OrderEventRepository;
import com.tapas.qb.ingestion.repository.OrderItemRepository;
import com.tapas.qb.ingestion.repository.OrderRepository;
import com.tapas.qb.ingestion.repository.ProductRepository;
import com.tapas.qb.ingestion.service.OrderService;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

@Service
public class OrderServiceImpl implements OrderService {

    private final OrderRepository orderRepository;
    private final OrderItemRepository orderItemRepository;
    private final OrderEventRepository orderEventRepository;
    private final ProductRepository productRepository;
    private final ObjectMapper objectMapper;

    public OrderServiceImpl(
            OrderRepository orderRepository,
            OrderItemRepository orderItemRepository,
            OrderEventRepository orderEventRepository,
            ProductRepository productRepository,
            ObjectMapper objectMapper
    ) {
        this.orderRepository = orderRepository;
        this.orderItemRepository = orderItemRepository;
        this.orderEventRepository = orderEventRepository;
        this.productRepository = productRepository;
        this.objectMapper = objectMapper;
    }

    @Override
    @Transactional
    public OrderCreateResponse createOrder(OrderCreateRequest request) {
        // 1. Compute totals
        BigDecimal totalAmount = request.items().stream()
                .map(i -> i.unitPrice().multiply(BigDecimal.valueOf(i.quantity())))
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        // 2. Save order
        Order order = new Order();
        order.setMerchantId(request.merchantId());
        order.setOrderDate(request.orderDate());
        order.setCurrency(request.currency());
        order.setTotalAmount(totalAmount);
        order = orderRepository.save(order);

        // 3. Save order items
        for (OrderItemRequest itemReq : request.items()) {
            OrderItem item = new OrderItem();
            item.setOrderId(order.getId());
            item.setProductId(itemReq.productId());
            item.setQuantity(itemReq.quantity());
            item.setUnitPrice(itemReq.unitPrice());
            item.setLineAmount(
                    itemReq.unitPrice().multiply(BigDecimal.valueOf(itemReq.quantity()))
            );
            orderItemRepository.save(item);
        }

        // 4. Create OUTBOX ROW FIRST (NO PAYLOAD YET)
        OrderEvent event = new OrderEvent();
        event.setOrderId(order.getId());
        event.setMerchantId(request.merchantId());
        event.setEventType("ORDER_CREATED");
        event.setCreatedAt(Instant.now());
        event.setProcessed(false);

        // First save — DB assigns event.id here
        event = orderEventRepository.save(event);

        // 5. Build payload ITEMS (after event.id exists)
        List<OrderCreatedEventPayload.Item> payloadItems = new ArrayList<>();
        for (OrderItemRequest itemReq : request.items()) {
            Long categoryId =
                    productRepository.findCategoryIdByProductId(itemReq.productId());
            payloadItems.add(
                    new OrderCreatedEventPayload.Item(
                            itemReq.productId(),
                            categoryId,
                            itemReq.quantity(),
                            itemReq.unitPrice(),
                            itemReq.unitPrice()
                                    .multiply(BigDecimal.valueOf(itemReq.quantity()))
                    )
            );
        }

        // 6. Build payload WITH eventId
        OrderCreatedEventPayload payload =
                new OrderCreatedEventPayload(
                        event.getId(),              // ✅ real outbox id
                        order.getId(),
                        request.merchantId(),
                        order.getOrderDate(),
                        request.currency(),
                        payloadItems
                );

        try {
            event.setPayload(objectMapper.writeValueAsString(payload));
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Failed to serialize OrderCreatedEventPayload", e);
        }

        // 7. UPDATE SAME ROW with payload
        orderEventRepository.save(event);

        // 8. Return response
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
