package com.tapas.qb.forecasting.consumer;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tapas.qb.forecasting.dto.OrderEventPayload;
import com.tapas.qb.forecasting.service.CategorySalesAggregator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class OrderEventsConsumer {

    private static final Logger log =
            LoggerFactory.getLogger(OrderEventsConsumer.class);

    private final ObjectMapper objectMapper;
    private final CategorySalesAggregator aggregator;

    public OrderEventsConsumer(ObjectMapper objectMapper,
                               CategorySalesAggregator aggregator) {
        this.objectMapper = objectMapper;
        this.aggregator = aggregator;
    }

    @KafkaListener(
            topics = "order-events",
            containerFactory = "kafkaListenerContainerFactory"
    )
    public void consume(String payload) throws JsonProcessingException {
        try {
            OrderEventPayload event =
                    objectMapper.readValue(payload, OrderEventPayload.class);

            aggregator.aggregate(event);

        } catch (Exception e) {
            log.error(" Failed to process event payload", e);
            throw e; // Kafka retry
        }
    }
}


