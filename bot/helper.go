package bot

import (
	"encoding/hex"
	"fmt"

	"github.com/ethereum/go-ethereum/crypto"
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

func getAddressFromSignature(message, signatureHex string) (string, error) {
	message = fmt.Sprintf("\x19Ethereum Signed Message:\n%d%s", len(message), message)
	messageHash := crypto.Keccak256Hash([]byte(message))

	signatureBytes, err := hex.DecodeString(signatureHex[2:])
	if err != nil {
		return "", err
	}

	signatureBytes[64] -= 27

	publicKey, err := crypto.SigToPub(messageHash.Bytes(), signatureBytes)
	if err != nil {
		return "", err
	}

	recoveredAddress := crypto.PubkeyToAddress(*publicKey).Hex()
	return recoveredAddress, nil
}
