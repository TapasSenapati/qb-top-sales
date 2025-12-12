package com.tapas.qb.ingestion.service;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/debug")
public class DebugKafkaController {

    private final DebugKafkaProducer producer;

    public DebugKafkaController(DebugKafkaProducer producer) {
        this.producer = producer;
    }

    @PostMapping("/kafka")
    public ResponseEntity<Void> send(@RequestParam String msg) {
        producer.sendTest(msg);
        return ResponseEntity.accepted().build();
    }
}
