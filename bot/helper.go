package bot

import (
	"github.com/gin-gonic/gin"
	tele "gopkg.in/telebot.v4"
)

func getUserLinkString(user *tele.User) string {
	return MustLocalize("ModeMarkdownV2.Link2User", gin.H{
		"User": user.FirstName + " " + user.LastName,
		"ID":   user.ID,
	})
}

func getUserLinkStruct(user *tele.User) gin.H {
	return gin.H{
		"User": getUserLinkString(user),
	}
}
