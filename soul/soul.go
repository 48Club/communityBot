package soul

import (
	"context"
	"math/big"

	"github.com/48Club/communityBot/sql"
	"github.com/ethereum/go-ethereum"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/ethclient"
	tele "gopkg.in/telebot.v4"
)

var (
	ec       = &ethclient.Client{}
	bscRPC   = "https://0.48.club"
	contract = common.HexToAddress("0x928dC5e31de14114f1486c756C30f39Ab9578A92")
	spabi    = getAbi()
)

func init() {
	var err error
	ec, err = ethclient.Dial(bscRPC)
	if err != nil {
		panic(err)
	}

}

func CheckSoulPoint(c *tele.User) SP_STATUS { // if not bind, return -1
	user, err := sql.GetUser(c.ID)
	if err != nil {
		return SP_VALID
	}
	if user.Address == nil {
		return SP_NOT_BIND
	}
	return GetSoulPoint(*user.Address)
}

type SP_STATUS int

const (
	SP_NOT_BIND   SP_STATUS = -1
	SP_VALID      SP_STATUS = 1
	SP_NOT_ENOUGH SP_STATUS = 0
)

func GetSoulPoint(a string) SP_STATUS { // if rpc error, return 1
	addr := common.HexToAddress(a)
	data, err := spabi.Pack("balanceOf", addr)
	if err != nil {
		return SP_VALID // api error, fallback to valid
	}

	hexResp, err := ec.CallContract(context.Background(), ethereum.CallMsg{
		To:   &contract,
		Data: data,
	}, nil)

	var balance *big.Int
	if err != nil {
		return SP_VALID // api error, fallback to valid
	}

	_ = spabi.UnpackIntoInterface(&balance, "balanceOf", hexResp)

	return SP_STATUS(balance.Int64())
}
