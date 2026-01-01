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
import java.util.Optional;

import com.tapas.qb.ingestion.domain.Merchant;
import com.tapas.qb.ingestion.repository.MerchantRepository;

@Service
public class OrderServiceImpl implements OrderService {

        private final OrderRepository orderRepository;
        private final OrderItemRepository orderItemRepository;
        private final OrderEventRepository orderEventRepository;
        private final ProductRepository productRepository;
        private final MerchantRepository merchantRepository;
        private final ObjectMapper objectMapper;

        public OrderServiceImpl(
                        OrderRepository orderRepository,
                        OrderItemRepository orderItemRepository,
                        OrderEventRepository orderEventRepository,
                        ProductRepository productRepository,
                        MerchantRepository merchantRepository,
                        ObjectMapper objectMapper) {
                this.orderRepository = orderRepository;
                this.orderItemRepository = orderItemRepository;
                this.orderEventRepository = orderEventRepository;
                this.productRepository = productRepository;
                this.merchantRepository = merchantRepository;
                this.objectMapper = objectMapper;
        }

        @Override
        @Transactional
        public OrderCreateResponse createOrder(OrderCreateRequest request) {
                /*
                 * API-level idempotency using externalOrderId (client-provided UUID).
                 */
                Optional<Order> existingOrderOpt = orderRepository.findByExternalOrderId(request.externalOrderId());
                if (existingOrderOpt.isPresent()) {
                        // ... existing logic for skipping ...
                        Order existingOrder = existingOrderOpt.get();
                        System.out.println("Order with external ID '" + request.externalOrderId()
                                        + "' already exists. Skipping creation.");
                        return new OrderCreateResponse(
                                        existingOrder.getId(),
                                        existingOrder.getExternalOrderId(),
                                        existingOrder.getMerchantId(),
                                        existingOrder.getTotalAmount(),
                                        orderItemRepository.findByOrderId(existingOrder.getId()).size(),
                                        "SKIPPED_ALREADY_EXISTS");
                }

                // 2. Lookup Merchant for Currency Snapshot
                Merchant merchant = merchantRepository.findById(request.merchantId())
                                .orElseThrow(() -> new IllegalArgumentException(
                                                "Merchant not found: " + request.merchantId()));

                // 1. Compute totals
                BigDecimal totalAmount = request.items().stream()
                                .map(i -> i.unitPrice().multiply(BigDecimal.valueOf(i.quantity())))
                                .reduce(BigDecimal.ZERO, BigDecimal::add);

                // 2. Save order
                Order order = new Order();
                order.setExternalOrderId(request.externalOrderId());
                order.setMerchantId(request.merchantId());
                order.setOrderDate(request.orderDate());
                order.setTotalAmount(totalAmount);

                // SNAPSHOT STRATEGY:
                // Use request currency if provided and matches, else default to Merchant's base
                // currency
                // For this strict implementation, we trust the Merchant's base currency as the
                // source of truth
                order.setCurrency(merchant.getCurrency());

                order = orderRepository.save(order);

                // 3. Save order items
                for (OrderItemRequest itemReq : request.items()) {
                        OrderItem item = new OrderItem();
                        item.setOrderId(order.getId());
                        item.setProductId(itemReq.productId());
                        item.setQuantity(itemReq.quantity());
                        item.setUnitPrice(itemReq.unitPrice());
                        item.setLineAmount(
                                        itemReq.unitPrice().multiply(BigDecimal.valueOf(itemReq.quantity())));
                        orderItemRepository.save(item);
                }

                // 4. Build payload items with category lookups
                List<OrderCreatedEventPayload.Item> payloadItems = new ArrayList<>();
                for (OrderItemRequest itemReq : request.items()) {
                        Long categoryId = productRepository.findCategoryIdByProductId(itemReq.productId());
                        payloadItems.add(
                                        new OrderCreatedEventPayload.Item(
                                                        categoryId,
                                                        itemReq.quantity(),
                                                        itemReq.unitPrice()
                                                                        .multiply(BigDecimal
                                                                                        .valueOf(itemReq.quantity()))));
                }

                // 5. Build payload (orderId used for downstream idempotency)
                OrderCreatedEventPayload payload = new OrderCreatedEventPayload(
                                order.getId(), // orderId - used for idempotency downstream
                                request.merchantId(),
                                order.getOrderDate(),
                                payloadItems);

                // 6. Create and save outbox event
                OrderEvent event = new OrderEvent();
                event.setOrderId(order.getId());
                event.setMerchantId(request.merchantId());
                event.setEventType("ORDER_CREATED");
                event.setCreatedAt(Instant.now());
                event.setProcessed(false);

                try {
                        event.setPayload(objectMapper.writeValueAsString(payload));
                } catch (JsonProcessingException e) {
                        throw new RuntimeException("Failed to serialize OrderCreatedEventPayload", e);
                }

                orderEventRepository.save(event);

                // 8. Return response
                return new OrderCreateResponse(
                                order.getId(),
                                order.getExternalOrderId(),
                                request.merchantId(),
                                totalAmount,
                                request.items().size(),
                                "CREATED");
        }

}
