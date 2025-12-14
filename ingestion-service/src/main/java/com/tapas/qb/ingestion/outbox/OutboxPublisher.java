package com.tapas.qb.ingestion.outbox;

import com.tapas.qb.ingestion.domain.OrderEvent;
import com.tapas.qb.ingestion.repository.OrderEventRepository;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;

@Component
public class OutboxPublisher {

    private static final String TOPIC = "order-events";

    private final OrderEventRepository orderEventRepository;
    private final KafkaTemplate<String, String> kafkaTemplate;

    public OutboxPublisher(OrderEventRepository orderEventRepository,
                           KafkaTemplate<String, String> kafkaTemplate) {
        this.orderEventRepository = orderEventRepository;
        this.kafkaTemplate = kafkaTemplate;
    }

    @Scheduled(fixedDelay = 5000)
    @Transactional
    public void publish() {
        List<OrderEvent> events =
                orderEventRepository.findTop100ByProcessedFalseOrderByCreatedAtAsc();

        for (OrderEvent event : events) {
            // key = orderId for ordering guarantees
            kafkaTemplate.send(
                    TOPIC,
                    event.getOrderId().toString(),
                    event.getPayload()
            );

            event.setProcessed(true);
            event.setProcessedAt(Instant.now());
            orderEventRepository.save(event);
        }
    }
}
