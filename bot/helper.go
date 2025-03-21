package bot

import (
	"github.com/gin-gonic/gin"
	tele "gopkg.in/telebot.v4"
)

func getUserWhitID(user *tele.User) gin.H {
	return gin.H{
		"User": user.FirstName + " " + user.LastName,
		"ID":   user.ID,
	}
}
