package com.tapas.qb.aggregation.consumer;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tapas.qb.aggregation.dto.OrderEventPayload;
import com.tapas.qb.aggregation.service.CategorySalesAggregator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

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
    public void consume(List<String> payloads) throws JsonProcessingException {
        try {
            var events = new ArrayList<OrderEventPayload>();
            for(String payload: payloads) {
                events.add(objectMapper.readValue(payload, OrderEventPayload.class));
            }

            aggregator.aggregate(events);

        } catch (Exception e) {
            log.error(" Failed to process event payload", e);
            throw e; // Kafka retry
        }
    }
}


