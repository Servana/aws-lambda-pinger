Globals = [:]
pipeline {
  agent {
    label any
  }
  options{
    timeout(time:2,unit:'HOURS')
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '5'))
    timestamps()
  }
  environment{
    AWS_DEFAULT_REGION = 'eu-west-1'
    AWS_DEFAULT_OUTPUT = 'json'
    ORGANISATION='XYZ'
    ENVIRONMENT='ABC'
    BUCKETNAME='s3-bucket-name-to-store-state'
    MONITORINGFREQUENCY='rate(5 minutes)' // Allowed values are described in https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html
    LOGLEVEL='INFO' // Allowed values are INFO and DEBUG
    CUSTOMMETRICFILTERS='disable' // Allowed values are enable and disable
    NOTIFICATIONS='slack'
  }
  stages {
   stage('CreateStateStore') {
      steps {
        createStateStore()
      }
   }
   stage("ChooseStrategy"){
      agent none
        steps{
          script {
            env.DEPLOY_TYPE = input message: 'Selection of deployment strategy is required',
                                  parameters: [
                                      choice(name: "choose the deployment strategy?", choices: 'config-only\nconfig-and-app', 
                                      description: 'Choose "config-only" if you want to deploy only config files')
                                  ]
          }
        }
   }
  stage('ConfigUpdate') {
      steps {
        configUpload()
      }
   }
   stage('CodeBuild') {
      when {
        environment name:'DEPLOY_TYPE', value:'config-and-app'
      }
      steps {
        script{
        Globals.versiondetails = loadPropFile('version.prop')
        env.VERSION = "${Globals.versiondetails.majorVersion}.${Globals.versiondetails.minorVersion}.${Globals.versiondetails.patchVersion}"
        echo "Version is ${VERSION}"
        codeBuild(VERSION)
        }
      }
    }
    stage('CodeDeploy'){
      when {
        environment name:'DEPLOY_TYPE', value:'config-and-app'
      }
      steps {
        echo 'Applying CloudFormation Infra Updates...'
        sh '''
        	   fullPath=`pwd`
        	   set +e
               aws cloudformation deploy \
                	--template-file $fullPath/cfn/pingerCF.yaml \
                	--stack-name $BUCKETNAME-$ENVIRONMENT-stack \
                	--parameter-overrides Environment="$ENVIRONMENT" \
                                        Organisation="$ORGANISATION" \
                                        BucketName="$BUCKETNAME" \
                                        ArtifactName="pinger_$VERSION.zip" \
                                        MonitoringFrequency="$MONITORINGFREQUENCY" \
                                        CustomMetricFilters="$CUSTOMMETRICFILTERS" \
                	--capabilities CAPABILITY_IAM \
                2>fileout
                RESULT=$?
        		 set -e
        		 # Tolerate when no changes are required for stack updates
        		 if [ $RESULT != 0 ]; then
        				if ! grep -q \"No changes to deploy\" fileout; then
        				  echo 'Unacceptable return code encountered:' $RESULT
        				  cat fileout
        				  exit $RESULT
        				fi
        		 fi
        '''
        script {
          currentBuild.description = "Current Version is ${VERSION}"
        }
      }
    }
}
}

def loadPropFile(FILE){
  def content = readFile "${FILE}"
  Properties propsfile = new Properties()
  InputStream is = new ByteArrayInputStream(content.getBytes());
  propsfile.load(is)
  return propsfile
}

def createStateStore() {
   echo 'Creating S3 bucket to store the state'
   sh '''
    fullPath=`pwd`
    if ! aws s3api head-bucket --bucket $BUCKETNAME 2>/dev/null; then
      aws s3api create-bucket --bucket $BUCKETNAME --region $AWS_DEFAULT_REGION --create-bucket-configuration LocationConstraint=$AWS_DEFAULT_REGION
    fi
   '''
}

def configUpload() {
  echo 'Uploading configuration'
  sh '''
  fullPath=`pwd`
  aws s3 cp $fullPath/config.yaml s3://$BUCKETNAME/
  '''
}

def codeBuild(version){
    echo 'Building code artifact'
    sh '''
    fullPath=`pwd`
    virtualenv -p /usr/bin/python3 $fullPath/pvenv
    ls -lrt $fullPath/pvenv/bin
    cd $fullPath/pvenv/bin/ && . ./activate && cd $fullPath
    pip install -t . -r $fullPath/requirements.txt
    sed -e "s~specify-region~$AWS_DEFAULT_REGION~g" \
        -e "s~s3-bucket-name~$BUCKETNAME~g" \
        -e "s~none~$NOTIFICATIONS~g" \
        -e "s~log-level~$LOGLEVEL~g" $fullPath/pinger_template.py > $fullPath/pinger.py
    zip -r pinger_$VERSION.zip . -x "cfn/*" -x "pinger_template.py" -x ".git/*" -x "pvenv/*" -x "Images/*"
    aws s3 cp pinger_$VERSION.zip s3://$BUCKETNAME/
    echo '{}' > state_machine
    aws s3 cp $fullPath/state_machine s3://$BUCKETNAME/    
    '''
}