The link to the instructions on how to start the node: 
https://docs.eywa.fi/node-operators/instruction-for-node-operators

Validator round rules:
https://docs.eywa.fi/node-operators/validators-round/validators-round


# PoA Testnet
Currently, the EYWA Oracle Network consists only of nodes maintained by the EYWA technical team. During the PoA testnet, a new version of the network will be tested, in which node holders will be different independent participants (up to 40 participants). This is necessary to increase the decentralization of the project and trust in the network.


After the testnet phase is completed, there will be a transition in the mainnet from the current version to the new PoA version supported by independent participants. CLP and CDP will continue to operate on this version of the EYWA Oracle Network until the network transitions to full Roll-DPoS consensus mechanic.


# The main objectives of the PoA testnet


The PoA testnet is necessary to examine network performance with a large number of independent validators in PoA mode. This will allow our technical team to study network performance under real conditions of heterogeneous network connectivity, when nodes are deployed on different clusters geographically distributed across the planet.


During the testnet period, the number of validators in the PoA network will gradually increase from 10-11 to 40. This will allow to thoroughly test the mechanisms of connecting new participants to the network and study their impact on traffic on the network.


All PoA testnet participants will need to request EYWA-PoA tokens to get their node into the pool of active validators (see details in the section Instruction for node operators).


# PoA testnet participants
At this stage, the structure of the EYWA Oracle Network will consist of:


Nodes of the validator round participants.
Nodes of the EYWA team (initial set of 7 nodes)
Nodes of partners and early investors


# Threshold in BLS signature


EYWA Oracle Network uses BLS cryptography to sign blocks. During the consensus process, nodes send each other BLS signatures for blocks with cross-chain calls. Nodes that collect the required number of signatures for a particular block save it to the storage.


Currently, it takes ⅔*totalValidatorsNumber +1 to collect consensus. Depending on the EYWA technical team's decision, this value may be increased in order to make the consensus more resistant to attacks.


# Testing plan


Testing the processing of multiple transactions in a block + estimation of TPS under conditions of a network consisting of multiple independent participants.
Testing the processing of a set of blocks.
Testing epoch change by multisig command with N participants (maximum with 40).
Testing the soft-fork mechanism.
Testing of the mechanism for assessing the network availability according to metrics (number of oracles) for the full switching of the network operation on the new builds.
Testing of the mechanics of upgrading the build for the nodes which are lagged by versions.
Testing the network's resistance to attacks with fraudulent signatures (from an old epoch or a forged signature)
