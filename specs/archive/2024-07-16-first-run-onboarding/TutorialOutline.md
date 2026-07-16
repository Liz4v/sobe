Warnings (is Sobe for you?):

- The advantages of using the public cloud for drop box are:
  1. If you want, you may fully control the public address by using a domain you own.
  2. Whatever public addresses you use are permanently yours as long as your cloud account is in good standing.
  3. No worries about web server security as long as you only upload stuff meant to be public.
- If you just want to share files that are currently interesting to you, or want some kind of access control, I don't recommend sobe. Use established file sharing services such as Dropbox.com, Google Drive, Microsoft OneDrive.
- Public cloud services **will** require your credit card, and often your ID too. This tutorial will help you set up products with excellent free tiers that can field a small but significant amount of traffic. If your files get a huge amount of traffic, you **will** get a bill, but you can (and should) set a budget cap.
- I, the sole author of Sobe, am an AWS specialist, and that's why Sobe and this tutorial are all-AWS. But if you already use a different public cloud service (GCP, Azure, Cloudflare, Bunny.net, Scaleway, etc.), do open an issue explaining your setup because I'm interested in expanding support.

Create an AWS account:

- Link.
- You will get access to AWS console.
- Use a region that makes sense for you. Remember your region. If unsure, us-east-1 (N. Virginia) works. Remember your region.
  - [Changed during implementation (2026-07-15): region guidance moved to the "Create a bucket" section of `docs/tutorial.md`, since only the bucket is regional. The other sections now note their side of it: CloudFront and IAM are global, and ACM's region is forced to us-east-1.]
- Use the top bar to search for AWS product names.
- Go to Billing and Cost Management. Click Budgets. Set a hard limit.
  - A really low limit like $5 or $1 is the best place to start.
  - An alert at 80% is also a good idea.
  - My drop box has never cost more than 4 cents in any individual month.

Create a bucket:

- Name it whatever. If the name you want is taken, use account regional namespace.
- Leave all remaining settings at default.
- Upload an example file. If you have an index.html handy, that's even better.

Create a CloudFront distribution:

- Free works. I have Pay-as-you-go because I set it up before fixed plans existed, and I have never surpassed the free tier.
- Name it whatever, "drop box" works. Copy-paste the name to the description. Don't set the domain yet, we'll cover it later.
- Origin type Amazon S3. For S3 origin, click Browse to find the bucket you just created.
- Leave all remaining settings at default. S3 permissions will be automatically updated for CloudFront.
- Note the distribution ID (E1111111111111) and distribution domain name (d2222222222222.cloudfront.net).
- Test your example file by requesting it through the distribution domain name.
- This cloudfront.net subdomain is yours now. You can stick with it or, later in this tutorial, I'll explain how to use your own domain.

Install sobe:

- Install with `uv tool install sobe` or `pip install sobe`, whichever works for you. I like [uv](https://github.com/astral-sh/uv#installation).
- Run `sobe` once. If no config file exists yet, it creates one and tells you where, then exits so you can edit it.
- Edit the config file: set `storage.bucket` to your bucket name and `cache.distribution` to the distribution ID you noted above. Set `url` to your CloudFront domain name for now (e.g. `https://d2222222222222.cloudfront.net/`).
- Save the config file. We will need that for our next section.

Create IAM (Identity and Access Management) access for sobe:

- Click IAM users, Create user. Pick a username, e.g. `drop-box`.
- Leave everything blank for now and just create the user.
- You'll be back to a user list. At the right, click Add permissions, Create inline policy, JSON.
- Run `sobe --policy` to get the JSON to fill up here.
- Scroll down to click Next. Call the policy name "sobe" and click Create policy to finish.
- On the top right, click Create an access key, Other.
- Continue until you see **Retrieve access keys**. You will need these keys.
- Fill in `aws_access_key_id` and `aws_secret_access_key` into the `[target.main.aws_session]` table in the config file. Don't forget to remove the `#` prefixes.
- Also set your `region_name` to the same region you created your S3 bucket in.
- Sobe should be fully functional now. Publish a file using it.

What will your domain be?

- Domains are **not** free but they come on pretty cheap annual cost (unless you want an expensive TLD like `.car`) and many registrars let you pay several years in advance, just in case.
- Use whatever registrar you like, except GoDaddy. GoDaddy is all dark patterns.
- Here's an affiliate link with $2 off if you want to tip: https://hover.com/Fb7kBrgy
- If you want to use your apex domain, you will have to use Route53, which is $0.50/mo.
  Otherwise you can use your registrar's DNS server, which AFAIK is always included.
- I use a subdomain (e.g. `files.example.com`) so I don't pay for Route53. All I need is a CNAME record.
  | Type | Host | Value |
  |-|-|-|
  | CNAME | files | d2222222222222.cloudfront.net |

Create an ACM Certificate:

- For this one, region must be us-east-1.
- Request, Request a public certificate, fill FQDN exactly right.
- Leave all remaining settings at default.
- It will say Pending validation. In the Domains section it's telling you what the records must look like. Example:
  - Domain: `files.example.com`
  - Status: Pending validation
  - CNAME name: `_44444444444444444444444444444444.files.example.com.`
  - CNAME value: `_55555555555555555555555555555555.jjjjjjjjjj.acm-validations.aws.`
- Create the requested CNAME in your registrar.
  | Type | Host | Value |
  |-|-|-|
  | CNAME | _44444444444444444444444444444444.files | _55555555555555555555555555555555.jjjjjjjjjj.acm-validations.aws |
  | CNAME | files | d2222222222222.cloudfront.net |
- You will usually have to wait for a few minutes until it works.
- Leave the validation there permanently so the certificate auto-renews.

Back to CloudFront

- Click the distribution ID to see details. At the bottom center you will see an empty list of Alternate domain names.
- Click add domain, type the FQDN, select the certificate, complete.
- The distribution will take a minute or two to update.
- Test your own domain with your own drop box! Yay!
- Edit your config file again to correct the public URL.
