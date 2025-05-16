# CDC

The IDE interface calls this and then only receives at the end currently, as it's not streaming until the end, currently. Also there's a question about how that will work. But what about running Postgres as the memory checkpointer, and then using change data capture, subscribing to the stream, and then the "controller AI" can interrupt, add messages, cancel, etc.?