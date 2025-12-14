package com.tapas.qb.ingestion.outbox;

import com.tapas.qb.ingestion.domain.OrderEvent;
import com.tapas.qb.ingestion.repository.OrderEventRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;

@Component
@Slf4j
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
        log.info("OutboxPublisher tick");
        List<OrderEvent> events =
                orderEventRepository.findTop100ByProcessedFalseOrderByCreatedAtAsc();
        log.info("🔁 Found {} unprocessed events", events.size());
        for (OrderEvent event : events) {
            // key = orderId for ordering guarantees
            kafkaTemplate.send(TOPIC, event.getOrderId().toString(), event.getPayload())
                    .whenComplete((result, ex) -> {
                        if (ex != null) {
                            log.error("Failed to publish event {}", event.getId(), ex);
                        } else {
                            log.info("Published event {} to Kafka partition {} offset {}",
                                    event.getId(),
                                    result.getRecordMetadata().partition(),
                                    result.getRecordMetadata().offset());
                        }
                    });

            event.setProcessed(true);
            event.setProcessedAt(Instant.now());
            orderEventRepository.save(event);
        }
    }
}
