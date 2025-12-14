package com.tapas.qb.forecasting.consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class OrderEventsConsumer {

    private static final Logger log =
            LoggerFactory.getLogger(OrderEventsConsumer.class);

    @KafkaListener(
            topics = "order-events",
            containerFactory = "kafkaListenerContainerFactory"
    )
    public void consume(String payload) {
        log.info("Received order event: {}", payload);
    }
}
