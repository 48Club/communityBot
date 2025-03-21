package main

import (
	"log"
	"os"
	"time"

	"github.com/48Club/communityBot/bot"
	tele "gopkg.in/telebot.v4"
)

func main() {
	pref := tele.Settings{
		Token:  os.Getenv("TOKEN"),
		Poller: &tele.LongPoller{Timeout: 10 * time.Second},
	}

	b, err := tele.NewBot(pref)
	if err != nil {
		log.Panic(err)
		return
	}

	bot.AddHandler(b)
	bot.Start(b)
}
