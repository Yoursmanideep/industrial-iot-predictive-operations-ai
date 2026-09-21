let
    CallMachineFailureRisk = (
        endpointUrl as text,
        tenantId as text,
        clientId as text,
        clientSecret as text,
        inputData as record
    ) as any =>
    let
        tokenUrl = "https://login.microsoftonline.com/" & tenantId & "/oauth2/v2.0/token",
        tokenBody =
            "client_id=" & Uri.EscapeDataString(clientId) &
            "&scope=https%3A%2F%2Fapi.fabric.microsoft.com%2F.default" &
            "&client_secret=" & Uri.EscapeDataString(clientSecret) &
            "&grant_type=client_credentials",
        tokenResponse = Web.Contents(
            tokenUrl,
            [
                Headers = [#"Content-Type" = "application/x-www-form-urlencoded"],
                Content = Text.ToBinary(tokenBody)
            ]
        ),
        tokenJson = Json.Document(tokenResponse),
        accessToken = tokenJson[access_token],
        requestBody = Json.FromValue(inputData),
        response = Web.Contents(
            endpointUrl,
            [
                Headers = [
                    #"Content-Type" = "application/json",
                    #"Authorization" = "Bearer " & accessToken
                ],
                Content = requestBody
            ]
        ),
        responseJson = Json.Document(response)
    in
        responseJson
in
    CallMachineFailureRisk
