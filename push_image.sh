docker build -t gmwee_chat .
docker tag gmwee_chat:latest registry.teefusion.net/tier-i/gmwee:dev
docker push registry.teefusion.net/tier-i/gmwee:dev
